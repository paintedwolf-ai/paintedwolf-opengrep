(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (let ((not (lambda args #f))) (if (not (string=? value "safe")) #f (sink value))))
(register handler)
