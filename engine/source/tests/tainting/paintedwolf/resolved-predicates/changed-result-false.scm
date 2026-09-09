(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (let ((allowed (string=? value "safe"))) (set! allowed #f) (if allowed #f (sink value))))
(register handler)
