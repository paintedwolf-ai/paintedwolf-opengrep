(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (string=? "safe" value) (sink value) #f))
(register handler)
