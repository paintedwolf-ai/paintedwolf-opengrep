(define (conditions)
  (sink (if #f (source) "fixed"))
  ;; ruleid: flow
  (sink (if #t (source) "fixed"))
  ;; ruleid: flow
  (sink (if 0 (source) "fixed"))
  ;; ruleid: flow
  (sink (if "" (source) "fixed"))
  ;; ruleid: flow
  (sink (if '() (source) "fixed"))
  (sink (if '#f (source) "fixed"))
  (sink (and #f (source)))
  (sink (or #t (source)))
  ;; ruleid: flow
  (sink (and #t (source)))
  ;; ruleid: flow
  (sink (or #f (source)))
  (sink (or 0 (source)))
  ;; ruleid: flow
  (sink (and '() (source)))
  (and #f (sink (source)))
  (or #t (sink (source))))
