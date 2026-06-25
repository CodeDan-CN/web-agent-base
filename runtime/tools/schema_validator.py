from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


class SchemaValidationResult:
    """
    JSON Schema 校验结果。

    Attributes:
        valid (bool): 是否通过。
        missing_params (list[str]): 缺失参数。
        error (str | None): 错误信息。
    """

    def __init__(
        self,
        valid: bool,
        missing_params: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        """
        初始化校验结果。
        """
        self.valid = valid
        self.missing_params = missing_params or []
        self.error = error


class JsonSchemaValidator:
    """
    JSON Schema 校验器。
    """

    def validate(self, schema: dict, payload: dict) -> SchemaValidationResult:
        """
        校验对象。

        Args:
            schema (dict): JSON Schema。
            payload (dict): 待校验对象。

        Returns:
            SchemaValidationResult: 校验结果。
        """
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
        if not errors:
            return SchemaValidationResult(valid=True)
        missing_params = self._missing_required(errors)
        if missing_params:
            return SchemaValidationResult(valid=False, missing_params=missing_params)
        return SchemaValidationResult(valid=False, error=self._format_error(errors[0]))

    def ensure_valid(self, schema: dict, payload: dict) -> None:
        """
        确保对象通过校验。

        Args:
            schema (dict): JSON Schema。
            payload (dict): 待校验对象。

        Raises:
            ValidationError: 校验失败。
        """
        Draft202012Validator(schema).validate(payload)

    def _missing_required(self, errors: list[ValidationError]) -> list[str]:
        """
        提取缺失必填参数。

        Args:
            errors (list[ValidationError]): 校验错误。

        Returns:
            list[str]: 缺失字段。
        """
        missing: list[str] = []
        for error in errors:
            if error.validator != "required":
                continue
            for field in error.validator_value:
                if field not in error.instance:
                    missing.append(str(field))
        return missing

    def _format_error(self, error: ValidationError) -> str:
        """
        格式化校验错误。

        Args:
            error (ValidationError): 校验错误。

        Returns:
            str: 错误信息。
        """
        path = ".".join(str(item) for item in error.path)
        return f"{path}: {error.message}" if path else error.message
