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

    p = progress_bar(500)
    try:
        for i in range(500):
            if i < 20:
                time.sleep(0.9)
            else:
                time.sleep(i%20*0.1)
            p += 1
    #        if i % 50 == 0:
    #            print()
    finally:
        p.close()
