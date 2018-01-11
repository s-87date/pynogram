### Benchmark on complex puzzles (remove `2>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643/1177288

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pyngrm --pbn $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done

for i in football einstein MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pyngrm --board $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| Name      | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
|-- webpbn.com --                                                                     |
| 1611      | 3.6           | 6             | 1                    | 100              |
| 1694      | 9.9           | 18            | 5                    | 100              |
| **6739**  | 7.8           | 14            | 6                    | **98.56**        |
| 4645      | 16            | 31            | 1                    | 100              |
| 2040      | 42            | 77            | 4                    | 100              |
| **2712**  | 33            | 60            | 5                    | **54.78**        |
| **6574**  | 3.6           | 6.3           | 6                    | **29.6**         |
| **8098**  | 0.9           | 1.5           | 1                    | **0**            |
| **2556**  | 1.7           | 2.9           | 2                    | **92.72**        |
|-- Local --                                                                          |
| [football](../examples/football.txt) | 0.7   | 1.1   | 1            | 100              |
| [einstein](../examples/einstein.txt) | 2.9   | 5.0   | 0            | 100              |
| [MLP](../examples/MLP.txt)           | 24    | 47    | 3            | 100              |