import charmap

cm = charmap.charmap()
for i in cm.int_to_char.keys():
    if cm.char_to_int[cm.int_to_char[i]] != i:
        print("Mapping mismatch!")
        print("i:", i)
        print("i_to_c:", cm.int_to_char[i])
        print("i_to_c_to_i:", cm.char_to_int[cm.int_to_char[i]])

print("Test Done")
