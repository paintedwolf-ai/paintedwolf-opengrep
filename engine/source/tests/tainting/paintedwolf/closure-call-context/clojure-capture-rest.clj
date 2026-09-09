(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [& args] value)] (sink (helper "safe" "more"))))
(register handler)
