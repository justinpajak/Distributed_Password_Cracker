# How I was thinking iterating through the possible permutations should work - replace chr() with our int_to_char()
n = 26
seq = [0, 0] # start sequence
while seq != [3, 0, 0]: # end sequence
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

# Decoding all possible values of i for passwords of length 3
n = 26
length = 3
for i in range(0, n**length):
    seq = []
    s = i
    while s > 0:
        seq.append(chr(s%n + 65))
        s = s//n
    print(seq)
        

