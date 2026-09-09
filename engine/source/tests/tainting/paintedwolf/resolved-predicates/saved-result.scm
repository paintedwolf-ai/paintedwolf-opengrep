(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ok: predicate
 (let ((allowed (string=? value "safe"))) (if allowed (sink value) #f)))
(register handler)
