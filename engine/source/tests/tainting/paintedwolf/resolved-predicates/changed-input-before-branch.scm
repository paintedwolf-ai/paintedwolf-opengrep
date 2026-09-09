(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (let ((allowed (string=? value "safe"))) (set! value (source)) (if allowed (sink value) #f)))
(register handler)
