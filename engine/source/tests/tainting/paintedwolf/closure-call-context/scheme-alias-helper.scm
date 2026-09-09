(define (handler value)
;; ruleid: closure-context
 (let* ((helper (lambda (ignored) value)) (other helper)) (sink (other "safe"))))
(register handler)
