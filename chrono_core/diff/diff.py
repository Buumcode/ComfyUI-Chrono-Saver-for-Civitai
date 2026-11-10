class WorkflowDiff:
    """
    Сравнение двух WorkflowReport.

    Показывает изменения
    в семантическом виде.
    """


    def compare(
        self,
        old,
        new,
    ):

        result = {
            "changed": {},
            "added": {},
            "removed": {},
        }


        old_data = old.to_dict()
        new_data = new.to_dict()


        keys = set(
            old_data.keys()
        ) | set(
            new_data.keys()
        )


        for key in keys:

            old_value = old_data.get(
                key
            )

            new_value = new_data.get(
                key
            )


            if old_value == new_value:
                continue


            if old_value is None:

                result["added"][key] = new_value

            elif new_value is None:

                result["removed"][key] = old_value

            else:

                result["changed"][key] = {
                    "from": old_value,
                    "to": new_value,
                }


        return result