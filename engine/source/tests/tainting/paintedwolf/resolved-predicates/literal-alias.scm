(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (let ((safe "safe")) (if (string=? value safe) (sink value) #f)))
(register handler)
