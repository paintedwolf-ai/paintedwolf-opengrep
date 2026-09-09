(use-modules ((web server) #:select (run-server)))
(define (handler request body)
  ;; ruleid: flow
  (sink body))
(run-server handler)
