(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (if (string=? value "safe") (let ((alias value)) (sink alias)) #f))
(register handler)
