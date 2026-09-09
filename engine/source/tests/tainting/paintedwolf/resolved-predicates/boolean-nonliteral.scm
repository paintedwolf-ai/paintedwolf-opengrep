(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (sink (string=? value (source))))
(register handler)
