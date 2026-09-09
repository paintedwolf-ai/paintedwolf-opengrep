(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (string=? value "safe") (begin (set! value "other") (sink value)) #f))
(register handler)
