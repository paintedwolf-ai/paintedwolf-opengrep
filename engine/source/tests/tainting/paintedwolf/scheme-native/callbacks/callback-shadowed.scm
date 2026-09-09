(use-modules ((web server) #:select (run-server)))
(define (run-server handler) (handler "fixed" "fixed"))
(define (handler request body) (sink body))
(run-server handler)
