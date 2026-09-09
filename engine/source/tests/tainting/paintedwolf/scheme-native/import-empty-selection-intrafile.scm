(use-modules ((web request)))
(define (handler request)
  ;; ruleid: flow
  (sink (request-uri request)))
