(define (parallel)
  (let ((base "fixed"))
    ;; ruleid: constant
    (observe base)))
(define (sequential)
  (let* ((base "fixed") (alias base))
    ;; ruleid: constant
    (observe alias)))
(define (sibling-uses-outer)
  (let ((base "fixed"))
    (let ((base "other") (alias base))
      (observe base)
      ;; ruleid: constant
      (observe alias))))
(define (overwritten)
  (let ((base "fixed"))
    (set! base (input))
    (observe base)))
(define (parallel-slot-values)
  (let ((base "fixed") (other (input)))
    ;; ruleid: constant
    (observe base)
    (observe other)))
(define (parallel-alias-independent)
  (let ((base "fixed"))
    (let ((alias base))
      (set! base "other")
      ;; ruleid: constant
      (observe alias))))
