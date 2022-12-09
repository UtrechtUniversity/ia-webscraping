import argparse
import os
import pyarrow.parquet as pq
from pathlib import Path


class ParquetSplitter:

    def __init__(self, input, outdir, split_col='job_tag'):
        if os.path.isfile(input):
            self.files = [input]
        else:
            self.files = Path(input).rglob('*.parquet')

        self.outdir = Path(outdir)
        self.split_col = split_col

    def make_job_folder(self, job_tag):
        Path(self.outdir / job_tag).mkdir(parents=True, exist_ok=True)

    def file_name(self, job_tag, i):
        return self.outdir / job_tag / Path(f"{job_tag}_({i}).parquet")

    def split_and_save(self):
        for file in self.files:
            print(f"Reading {file}")
            t = pq.read_table(file)
            p = t.to_pandas()

            split_vals = p[self.split_col].unique()

            for split_val in split_vals:
                print(f"Filtering '{split_val}'")

                self.make_job_folder(split_val)

                i = 0
                outfile = self.file_name(split_val, i)

                while outfile.is_file():
                    i += 1
                    outfile = self.file_name(split_val, i)

                p.loc[p[self.split_col] == split_val].to_parquet(outfile, index=False)
                print(f"Wrote {outfile}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='python parquet_file_split.py',
                description='Script splits Parquet-file(s) based on value of "job_tag" column')
    parser.add_argument("--input", type=str, required=True, help='Parquet file or folder with Parquet files to process')
    parser.add_argument("--outdir", type=str, required=True, help='Folder to write split files to')
    args = parser.parse_args()

    ps = ParquetSplitter(input=args.input, outdir=args.outdir)
    ps.split_and_save()
