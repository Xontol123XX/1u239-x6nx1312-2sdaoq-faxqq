import random
low = 5
high = 99

r = random.random()         # hasil antara 0 dan 1
biased_r = r ** 5           # bikin angka tinggi makin jarang
value = low + (high - low) * biased_r

print(value)