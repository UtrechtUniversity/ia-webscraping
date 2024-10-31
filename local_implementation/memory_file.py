from pathlib import Path

class MemoryFile:

    def __init__(self, file):
        self.memory_file = Path(file)
        self.memory_file.touch()
        self.read()

    def exists(self, item):
        return item in self.memories

    def read(self):
        self.memories = []
        with open(self.memory_file, 'r') as f:
            self.memories = f.read().splitlines()

    def store(self, item):
        self.read()
        self.memories.append(item)
        self.memories = list(set(self.memories))
        with open(self.memory_file, 'w') as f:
            f.write('\n'.join(self.memories))
