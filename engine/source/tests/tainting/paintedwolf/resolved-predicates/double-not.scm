(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (not (not (string=? value "safe"))) (sink value) #f))
(register handler)
