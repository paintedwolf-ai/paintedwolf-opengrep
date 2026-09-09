(defun direct ()
  ;; ruleid: lisp-bindings
  (sink (source)))
(defun local ()
  (let ((value (source)))
    ;; ruleid: lisp-bindings
    (sink value)))
(defun shadow ()
  (let ((value (source)))
    (let ((value "fixed"))
      ;; ok: lisp-bindings
      (sink value))))
(defun parallel ()
  (let ((outer "fixed"))
    (let ((outer (source)) (copy outer))
      ;; ok: lisp-bindings
      (sink copy))))
(defun sequential ()
  (let ((outer "fixed"))
    (let* ((outer (source)) (copy outer))
      ;; ruleid: lisp-bindings
      (sink copy))))
;; ok: lisp-bindings
'(sink (source))
