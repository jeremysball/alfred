#!/usr/bin/env guile
!#

;; A simple Lisp/Scheme program demonstrating key features

;; Define a recursive factorial function
(define (factorial n)
  (if (<= n 1)
      1
      (* n (factorial (- n 1)))))

;; Define a fibonacci function
(define (fibonacci n)
  (cond ((= n 0) 0)
        ((= n 1) 1)
        (else (+ (fibonacci (- n 1))
                 (fibonacci (- n 2))))))

;; Define a list operations function
(define (sum-list lst)
  (if (null? lst)
      0
      (+ (car lst) (sum-list (cdr lst)))))

;; Higher-order function example
(define (map-list fn lst)
  (if (null? lst)
      '()
      (cons (fn (car lst)) (map-list fn (cdr lst)))))

;; Main execution
(display "=== Lisp/Scheme Examples ===")
(newline)
(newline)

(display "Factorial of 5: ")
(display (factorial 5))
(newline)

(display "Factorial of 10: ")
(display (factorial 10))
(newline)
(newline)

(display "Fibonacci sequence (first 10):")
(newline)
(let loop ((i 0))
  (when (< i 10)
    (display "  fib(")
    (display i)
    (display ") = ")
    (display (fibonacci i))
    (newline)
    (loop (+ i 1))))
(newline)

(display "List operations:")
(newline)
(define my-list '(1 2 3 4 5))
(display "  Original list: ")
(display my-list)
(newline)
(display "  Sum of list: ")
(display (sum-list my-list))
(newline)
(display "  Doubled (using map): ")
(display (map-list (lambda (x) (* x 2)) my-list))
(newline)
(newline)

;; Closure example
(display "Closure example:")
(newline)
(define (make-counter)
  (let ((count 0))
    (lambda ()
      (set! count (+ count 1))
      count)))

(define counter (make-counter))
(display "  Counter calls: ")
(display (counter))
(display " ")
(display (counter))
(display " ")
(display (counter))
(newline)
(newline)

(display "=== Done! ===")
(newline)
