(use-modules ((guile) #:select ((string=? . same-string) not)))
(define (handler value)
;; ok: predicate
 (if (same-string value "safe") (sink value) #f))
(register handler)
