# Some simple traceable examples

import tracer, sys

def fizz(n):
    for i in range(n):
        if not i % 3 or not i % 5:
            buzz(i)

def buzz(x):
    if not x % 3 and not x % 5:
        print 'fizzbuzz'
    elif not x % 3:
        print 'fizz'
    elif not x % 5:
        print 'buzz'

def fizzrecur(n, y=False):
    if y:
        if not n % 3 and not n % 5:
            print 'fizzbuzz'
        elif not n % 3:
            print 'fizz'
        elif not n % 5:
            print 'buzz'
    else:
        for i in range(n):
            if not i % 3 or not i % 5:
                fizzrecur(i, True)

def fizzgen(n):
    def genfn():
        i = 0
        while i < n:
            yield i
            i += 1
    for i in genfn():
        if i % 2:
            print 'ok'

def fizzlambda(n):
    sys.stdout.write('\n'.join(filter(None,
        map(lambda i: 'fizzbuzz' if not i % 3 and not i % 5 else (
                'fizz' if not i % 3 else ('buzz' if not i % 5 else '')),
            range(n)))))

def fizzcomp(n):
    print '\n'.join('fizz' for i in range(n) if not i % 3)

def fizztrace(n):
    for i in range(n):
        tracer.val(i=i)
        if not i % 3 and not i % 5:
            print 'fizzbuzz'
        elif not i % 3:
            print 'fizz'
        elif not i % 5:
            print 'buzz'

def main():
    g = globals()
    for i in g:
        if i.startswith('fizz'):
            g[i](20)

if __name__ == "__main__":
    with tracer.Tracer('/tmp/fizz.pickle', stash_modules=True):
        main()
