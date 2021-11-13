n = 26
seq = [0, 0]
while seq != [3, 0, 0]:
    print(seq, ''.join(chr(c + 65) for c in seq))
    i = len(seq) - 1
    seq[-1] += 1
    while seq[i] > n-1:
        seq[i] = 0
        if i == 0:
            seq.insert(0, 0)
        else:
            i -= 1
            seq[i] += 1


n = 26
length = 3
for i in range(0, n**length):
    seq = []
    s = i
    while s > 0:
        seq.append(chr(s%n + 65))
        s = s//n
    print(seq)
        

