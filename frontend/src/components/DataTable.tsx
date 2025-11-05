import React from 'react';

type Column<T> = {
  header: string;
  accessor: (row: T) => React.ReactNode;
};

type DataTableProps<T> = {
  data: T[];
  columns: Column<T>[];
  emptyMessage?: string;
};

const DataTable = <T,>({ data, columns, emptyMessage = 'No results' }: DataTableProps<T>) => {
  if (!data.length) {
    return <div className="card">{emptyMessage}</div>;
  }

  return (
    <div className="card">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.header}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => (
                <td key={column.header}>{column.accessor(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
