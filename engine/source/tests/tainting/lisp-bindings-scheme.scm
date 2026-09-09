(define (direct)
  ;; ruleid: lisp-bindings
  (sink (source)))
(define (local)
  (let ((value (source)))
    ;; ruleid: lisp-bindings
    (sink value)))
(define (shadow)
  (let ((value (source)))
    (let ((value "fixed"))
      ;; ok: lisp-bindings
      (sink value))))
(define (parallel)
  (let ((outer "fixed"))
    (let ((outer (source)) (copy outer))
      ;; ok: lisp-bindings
      (sink copy))))
(define (sequential)
  (let ((outer "fixed"))
    (let* ((outer (source)) (copy outer))
      ;; ruleid: lisp-bindings
      (sink copy))))
;; ok: lisp-bindings
'(sink (source))
