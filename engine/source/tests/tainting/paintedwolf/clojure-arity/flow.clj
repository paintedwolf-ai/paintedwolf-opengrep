(defn echo [x] x)
;; ruleid: flow
(sink (echo (source)))
