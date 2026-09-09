(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (let ((alias value)) (if (string=? value "safe") (sink alias) #f)))
(register handler)
