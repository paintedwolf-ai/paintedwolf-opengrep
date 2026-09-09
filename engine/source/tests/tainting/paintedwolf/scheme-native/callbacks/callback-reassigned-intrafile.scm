(use-modules ((web server) #:select (run-server)))
(define (handler request body) (sink body))
(set! handler (lambda (request body) "fixed"))
(run-server handler)
