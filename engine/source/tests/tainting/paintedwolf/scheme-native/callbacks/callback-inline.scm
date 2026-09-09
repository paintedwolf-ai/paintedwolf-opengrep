(use-modules ((web server) #:select (run-server)))
(run-server (lambda (request body)
  ;; ruleid: flow
  (sink body)))
