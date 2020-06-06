import tqdm

class progress_bar():
    def __init__(self, n_tot):
        self.bar = tqdm.tqdm(total = n_tot, unit='points', ncols=80)
        self.n = 0

    def __add__(self, n):
        self.bar.update(n)
        self.n += n
        return self

    def close(self):
        self.bar.close()

if __name__ == '__main__':
    import time

    p = progress_bar(50)

    for i in range(50):
        time.sleep(0.01)
        p += 1

    p.close()