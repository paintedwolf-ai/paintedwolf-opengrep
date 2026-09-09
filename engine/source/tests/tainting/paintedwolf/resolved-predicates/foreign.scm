(use-modules ((application custom) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") (sink value) #f))
(register handler)
