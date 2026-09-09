(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (let ((alias value)) (if (string=? value "safe") (begin (set! value "other") (sink alias)) #f)))
(register handler)
