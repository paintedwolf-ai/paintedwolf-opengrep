(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (string=? value "safe") (begin (sink value) (sink value)) #f))
(register handler)
