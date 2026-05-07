package api

import "net/http"

type healthResponse struct {
	Status string `json:"status"`
	DB     string `json:"db"`
	LLM    string `json:"llm"`
}

func healthHandler(deps RouterDeps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		boolToStr := func(ok bool) string {
			if ok {
				return "up"
			}
			return "down"
		}
		dbOk := deps.HealthDB != nil && deps.HealthDB()
		status := "ok"
		if !dbOk {
			status = "degraded"
		}
		JSON(w, http.StatusOK, healthResponse{
			Status: status,
			DB:     boolToStr(dbOk),
			LLM:    boolToStr(deps.HealthLLM != nil && deps.HealthLLM()),
		})
	}
}
