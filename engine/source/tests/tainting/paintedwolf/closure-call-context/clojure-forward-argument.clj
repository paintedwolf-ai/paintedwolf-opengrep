(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [input] input)] (sink (helper value))))
(register handler)
