"use client";

import { useEffect, useState } from "react";
import { fetchDownloadFolder } from "@/lib/api/compilations";
import { readStored, writeStored } from "@/lib/storage";

const FOLDER_KEY = "compcreator-download-folder";

export type DownloadFolder = {
  folder: string;
  changeFolder: (value: string) => void;
};

/** The save folder, restored from local storage or the server default. */
export function useDownloadFolder(): DownloadFolder {
  const [folder, setFolder] = useState("");

  useEffect(() => {
    const stored = readStored(FOLDER_KEY);
    if (stored) {
      // The field starts empty so server HTML matches the first client render.
      // localStorage is only available after mount.
      // eslint-disable-next-line react-hooks/set-state-in-effect -- hydration-safe read
      setFolder(stored);
      return;
    }
    fetchDownloadFolder()
      .then((path) => {
        setFolder((current) => current || path);
      })
      .catch((caught: unknown) => {
        if (!(caught instanceof Error)) {
          throw caught;
        }
        // A blank folder tells the server to use Downloads.
      });
  }, []);

  function changeFolder(value: string): void {
    setFolder(value);
    writeStored(FOLDER_KEY, value);
  }

  return { folder, changeFolder };
}
