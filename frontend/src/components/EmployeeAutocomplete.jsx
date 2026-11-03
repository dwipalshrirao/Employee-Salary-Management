import { useState } from "react";
import { Autocomplete, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { listEmployees } from "../api/employees";
import { useDebounce } from "../hooks/useDebounce";

export default function EmployeeAutocomplete({ value, onChange, label = "Manager" }) {
  const [input, setInput] = useState("");
  const search = useDebounce(input, 300);
  const { data, isFetching } = useQuery({
    queryKey: ["employees", "manager-search", search],
    queryFn: () => listEmployees({ q: search, page_size: 10 }),
    enabled: search.length > 0,
  });
  const options = data?.items ?? [];
  const selected = options.find((option) => String(option.id) === String(value)) ?? null;

  return (
    <Autocomplete
      size="small"
      options={options}
      value={selected}
      inputValue={input}
      loading={isFetching}
      getOptionLabel={(option) => option.full_name}
      isOptionEqualToValue={(option, selectedOption) => option.id === selectedOption.id}
      onChange={(_, option) => onChange(option ? String(option.id) : "")}
      onInputChange={(_, nextInput) => setInput(nextInput)}
      noOptionsText={search ? "No employees found" : "Type to search"}
      renderInput={(params) => <TextField {...params} label={label} placeholder="Search manager" />}
    />
  );
}
