(define (handler request)
  ;; ruleid: flow
  (sink request)
  (set! request "fixed")
  (sink request))
(register handler)
