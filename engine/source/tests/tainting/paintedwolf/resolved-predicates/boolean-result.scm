(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (sink (string=? value "safe")))
(register handler)
