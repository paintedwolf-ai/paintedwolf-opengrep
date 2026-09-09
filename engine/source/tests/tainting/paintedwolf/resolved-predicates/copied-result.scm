(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (let* ((allowed (string=? value "safe")) (copy allowed)) (if copy (sink value) #f)))
(register handler)
