(use-modules ((guile) #:prefix core:))
(define (handler value)
;; ok: predicate
 (if (core:string=? value "safe") (sink value) #f))
(register handler)
