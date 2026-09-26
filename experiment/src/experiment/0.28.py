import numpy as np
import time

n = 4096

a = np.random.rand(n, n)
b = np.random.rand(n, n)

start = time.time()

c = a @ b

end = time.time()

print("time:", end - start, "seconds")