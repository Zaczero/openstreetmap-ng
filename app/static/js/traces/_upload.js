import { configureStandardForm } from "../_standard-form.js"

const tracesUploadBody = document.querySelector("body.traces-upload-body")
if (tracesUploadBody) {
    const uploadForm = tracesUploadBody.querySelector("form.upload-form")

    // On success callback, navigate to the new trace
    const onFormSuccess = ({ trace_id }) => {
        window.location = `/trace/${trace_id}`
    }

    configureStandardForm(uploadForm, onFormSuccess)
}
