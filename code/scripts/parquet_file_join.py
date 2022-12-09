import argparse
import os
import shutil
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path


class ParquetJoiner:

    def __init__(self, indir, outdir, basename, delete_originals=False, max_file_size=25):
        self.files = Path(indir).rglob('*.parquet')

        if not outdir is None:
            self.outdir = Path(outdir)
        else:
            self.outdir = Path(indir)

        assert isinstance(delete_originals, bool)
        self.delete_originals = delete_originals

        assert isinstance(max_file_size, int)
        self.max_file_size = round(max_file_size * 1e6)

        self.basename = basename
        self.outfile_counter = 0

    def get_file_name(self):
        file_name = self.outdir / Path(f"{self.basename}_({str(self.outfile_counter)}).parquet")
        self.outfile_counter += 1
        return file_name

    def copy_file(self, file):
        new_path = self.get_file_name()
        shutil.copy(file, new_path)
        if self.delete_originals:
            os.unlink(file)
        print(f"Copied '{file.name}' to '{new_path}'")

    def join_and_save(self, files_to_join):
        if len(files_to_join) == 0:
            return
        
        for file in files_to_join:
            if not 't_joined'in locals():
                t_joined = pq.read_table(file)
            else:
                t_joined = pa.concat_tables([t_joined, pq.read_table(file)])
        
        new_path = self.get_file_name()
        pq.write_table(t_joined, new_path)
        if self.delete_originals:
            for file in files_to_join:
                os.unlink(file)

        print(f"Combined {len(files_to_join)} files into '{new_path}'")

    def join(self):
        files_to_join = []
        approx_joined_size = 0
        for file in self.files:
            # print(f"Reading {file}")

            file_size = os.path.getsize(file)
            if file_size >= self.max_file_size:
                self.copy_file(file)
                continue

            approx_joined_size += file_size
            if approx_joined_size <= self.max_file_size:
                files_to_join.append(file)
            else:
                if len(files_to_join) == 1:
                    self.copy_file(files_to_join[0])
                else:
                    self.join_and_save(files_to_join)

                files_to_join = [file]
                approx_joined_size = file_size
        
        self.join_and_save(files_to_join)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='python parquet_filter.py',description='Combines Parquet files')
    parser.add_argument("--indir", type=str, required=True, help='Parquet file or folder with Parquet files to join')
    parser.add_argument("--outdir", type=str, help='Folder to write joined files to (if absent, input folder is used)')
    parser.add_argument("--basename", type=str, required=True, help='Basename of joined files')
    parser.add_argument("--delete-originals", action='store_true')
    parser.add_argument("--max-file-size", type=int, help='Maximum size of resulting files (MB)', default=25)

    args = parser.parse_args()

    ps = ParquetJoiner(indir=args.indir,
                       outdir=args.outdir,
                       basename=args.basename,
                       delete_originals=args.delete_originals,
                       max_file_size=args.max_file_size)
    ps.join()
