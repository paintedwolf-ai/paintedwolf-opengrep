(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [ignored enabled] (if enabled value "safe"))] (sink (helper value true))))
(register handler)
