#!/usr/bin/env python3
import json
import re

f = open("atlantic.txt", "r")

lines = f.read().split("\n")
print(f"Lines: {len(lines)}")

puzzles = {}
for line in lines:
    words = line.split(" ")
    date = None
    month = None
    year = None
    num = int(words[0])
    books = []
    title = []
    n = 1
    while n < len(words):
        word = words[n]
        if re.match("[-0-9]+/[0-9]", word):
            date = word
            month, year = date.split("/")
            if year > "76":
                year = "19" + year
            else:
                year = "20" + year
            date = f"{month}/{year}"
        elif date:
            for book in word.split(","):
                book = book.strip()
                if book:
                    books.append(book)
        else:
            title.append(word)
        n += 1

    t = " ".join(title)
    print(f"{num}: \"{t}\" [{date}]")
    puzzle = {
        "pub": "atlantic",
        "num": num,
        "title": t,
        "year": year,
        "month": month,
        "date": date,
        "books": sorted(books),
    }
    puzzles[num] = puzzle

outfile = open("atlantic.json", "w")
outfile.write(json.dumps(puzzles, indent=2, sort_keys=True))
