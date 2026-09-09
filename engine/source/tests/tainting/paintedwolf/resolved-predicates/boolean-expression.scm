(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (sink (string=? (source) "safe")))
(register handler)
