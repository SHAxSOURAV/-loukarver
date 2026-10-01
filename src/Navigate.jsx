import React from 'react'
import { useNavigate } from 'react-router-dom'
import { FaArrowLeft } from "react-icons/fa";
export const Navigate = ({title}) => {
    const navigate = useNavigate()
  return (
    <div className=''>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h1
            onClick={() => navigate(-1)}
            className="flex gap-3 cursor-pointer"
          >
            <button className="bg-[#B7835E] mt-[5px] text-sm w-5 h-5 rounded-full flex justify-center items-center text-white">
              <FaArrowLeft />
            </button>
            <span className="text-lg font-semibold">{title}</span>
          </h1>
          
        </div>
    </div>
  )
}
