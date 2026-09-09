(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (not (string=? value "safe")) #f (sink value)))
(register handler)
