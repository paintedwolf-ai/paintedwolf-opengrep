(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (sink (not (string=? value "safe"))))
(register handler)
