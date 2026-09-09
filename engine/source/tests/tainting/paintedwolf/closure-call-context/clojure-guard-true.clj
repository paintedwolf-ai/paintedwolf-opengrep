(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [enabled] (if enabled value "safe"))] (sink (helper true))))
(register handler)
